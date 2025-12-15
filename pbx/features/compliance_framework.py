"""
Compliance Framework
GDPR, SOC 2, and PCI DSS compliance features
"""
from datetime import datetime
from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class GDPRComplianceEngine:
    """
    GDPR compliance framework
    Data privacy and protection features
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize GDPR compliance engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get('gdpr.enabled', True)

        self.logger.info("GDPR Compliance Framework initialized")

    def record_consent(self, consent_data: Dict) -> bool:
        """
        Record user consent

        Args:
            consent_data: Consent information

        Returns:
            bool: True if successful
        """
        try:
            # GDPR requires explicit consent - no default to True
            if 'consent_given' not in consent_data:
                self.logger.error("consent_given is required for GDPR compliance")
                return False
                
            self.db.execute(
                """INSERT INTO gdpr_consent_records 
                   (extension, consent_type, consent_given, consent_date, ip_address)
                   VALUES (?, ?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO gdpr_consent_records 
                   (extension, consent_type, consent_given, consent_date, ip_address)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    consent_data['extension'],
                    consent_data['consent_type'],
                    consent_data['consent_given'],  # Explicit consent required
                    consent_data.get('consent_date', datetime.now()),
                    consent_data.get('ip_address')
                )
            )

            self.logger.info(
                f"Recorded consent for {consent_data['extension']}: {consent_data['consent_type']}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to record consent: {e}")
            return False

    def withdraw_consent(self, extension: str, consent_type: str) -> bool:
        """
        Withdraw user consent

        Args:
            extension: Extension number
            consent_type: Type of consent

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                """UPDATE gdpr_consent_records 
                   SET consent_given = ?, withdrawn_date = ?
                   WHERE extension = ? AND consent_type = ? AND consent_given = ?"""
                if self.db.db_type == 'sqlite'
                else """UPDATE gdpr_consent_records 
                   SET consent_given = %s, withdrawn_date = %s
                   WHERE extension = %s AND consent_type = %s AND consent_given = %s""",
                (False, datetime.now(), extension, consent_type, True)
            )

            self.logger.info(f"Withdrew consent for {extension}: {consent_type}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to withdraw consent: {e}")
            return False

    def get_consent_status(self, extension: str) -> List[Dict]:
        """
        Get consent status for extension

        Args:
            extension: Extension number

        Returns:
            List of consent records
        """
        try:
            result = self.db.execute(
                """SELECT * FROM gdpr_consent_records 
                   WHERE extension = ? 
                   ORDER BY consent_date DESC"""
                if self.db.db_type == 'sqlite'
                else """SELECT * FROM gdpr_consent_records 
                   WHERE extension = %s 
                   ORDER BY consent_date DESC""",
                (extension,)
            )

            consents = []
            for row in (result or []):
                consents.append({
                    'consent_type': row[2],
                    'consent_given': bool(row[3]),
                    'consent_date': row[4],
                    'withdrawn_date': row[5],
                    'ip_address': row[6]
                })

            return consents

        except Exception as e:
            self.logger.error(f"Failed to get consent status: {e}")
            return []

    def create_data_request(self, request_data: Dict) -> Optional[int]:
        """
        Create GDPR data request (access, portability, erasure)

        Args:
            request_data: Request information

        Returns:
            Request ID or None
        """
        try:
            self.db.execute(
                """INSERT INTO gdpr_data_requests 
                   (extension, request_type, status)
                   VALUES (?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO gdpr_data_requests 
                   (extension, request_type, status)
                   VALUES (%s, %s, %s)""",
                (
                    request_data['extension'],
                    request_data['request_type'],
                    'pending'
                )
            )

            # Get request ID
            result = self.db.execute(
                """SELECT id FROM gdpr_data_requests 
                   WHERE extension = ? AND request_type = ? 
                   ORDER BY requested_at DESC LIMIT 1"""
                if self.db.db_type == 'sqlite'
                else """SELECT id FROM gdpr_data_requests 
                   WHERE extension = %s AND request_type = %s 
                   ORDER BY requested_at DESC LIMIT 1""",
                (request_data['extension'], request_data['request_type'])
            )

            if result and result[0]:
                request_id = result[0][0]
                self.logger.info(
                    f"Created GDPR {request_data['request_type']} request for {request_data['extension']}"
                )
                return request_id

            return None

        except Exception as e:
            self.logger.error(f"Failed to create data request: {e}")
            return None

    def complete_data_request(self, request_id: int) -> bool:
        """
        Mark data request as completed

        Args:
            request_id: Request ID

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                """UPDATE gdpr_data_requests 
                   SET status = ?, completed_at = ?
                   WHERE id = ?"""
                if self.db.db_type == 'sqlite'
                else """UPDATE gdpr_data_requests 
                   SET status = %s, completed_at = %s
                   WHERE id = %s""",
                ('completed', datetime.now(), request_id)
            )

            self.logger.info(f"Completed GDPR data request {request_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to complete data request: {e}")
            return False

    def get_pending_requests(self) -> List[Dict]:
        """
        Get all pending GDPR data requests

        Returns:
            List of request dictionaries
        """
        try:
            result = self.db.execute(
                """SELECT * FROM gdpr_data_requests 
                   WHERE status = ? 
                   ORDER BY requested_at"""
                if self.db.db_type == 'sqlite'
                else """SELECT * FROM gdpr_data_requests 
                   WHERE status = %s 
                   ORDER BY requested_at""",
                ('pending',)
            )

            requests = []
            for row in (result or []):
                requests.append({
                    'id': row[0],
                    'extension': row[1],
                    'request_type': row[2],
                    'requested_at': row[4]
                })

            return requests

        except Exception as e:
            self.logger.error(f"Failed to get pending requests: {e}")
            return []


class SOC2ComplianceEngine:
    """
    SOC 2 Type II compliance framework
    Security and compliance controls
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize SOC 2 compliance engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get('soc2.enabled', True)

        self.logger.info("SOC 2 Compliance Framework initialized")

    def register_control(self, control_data: Dict) -> bool:
        """
        Register SOC 2 control

        Args:
            control_data: Control information

        Returns:
            bool: True if successful
        """
        try:
            # Check if control exists
            result = self.db.execute(
                "SELECT id FROM soc2_controls WHERE control_id = ?"
                if self.db.db_type == 'sqlite'
                else "SELECT id FROM soc2_controls WHERE control_id = %s",
                (control_data['control_id'],)
            )

            if result and result[0]:
                # Update
                self.db.execute(
                    """UPDATE soc2_controls 
                       SET control_category = ?, description = ?, 
                           implementation_status = ?, test_results = ?
                       WHERE control_id = ?"""
                    if self.db.db_type == 'sqlite'
                    else """UPDATE soc2_controls 
                       SET control_category = %s, description = %s, 
                           implementation_status = %s, test_results = %s
                       WHERE control_id = %s""",
                    (
                        control_data.get('control_category'),
                        control_data.get('description'),
                        control_data.get('implementation_status'),
                        control_data.get('test_results'),
                        control_data['control_id']
                    )
                )
            else:
                # Insert
                self.db.execute(
                    """INSERT INTO soc2_controls 
                       (control_id, control_category, description, implementation_status)
                       VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == 'sqlite'
                    else """INSERT INTO soc2_controls 
                       (control_id, control_category, description, implementation_status)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        control_data['control_id'],
                        control_data.get('control_category'),
                        control_data.get('description'),
                        control_data.get('implementation_status', 'pending')
                    )
                )

            self.logger.info(f"Registered SOC 2 control: {control_data['control_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register control: {e}")
            return False

    def update_control_test(self, control_id: str, test_results: str) -> bool:
        """
        Update control test results

        Args:
            control_id: Control ID
            test_results: Test results

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                """UPDATE soc2_controls 
                   SET test_results = ?, last_tested = ?
                   WHERE control_id = ?"""
                if self.db.db_type == 'sqlite'
                else """UPDATE soc2_controls 
                   SET test_results = %s, last_tested = %s
                   WHERE control_id = %s""",
                (test_results, datetime.now(), control_id)
            )

            self.logger.info(f"Updated test results for control {control_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update control test: {e}")
            return False

    def get_all_controls(self) -> List[Dict]:
        """
        Get all SOC 2 controls

        Returns:
            List of control dictionaries
        """
        try:
            result = self.db.execute(
                "SELECT * FROM soc2_controls ORDER BY control_id"
            )

            controls = []
            for row in (result or []):
                controls.append({
                    'control_id': row[1],
                    'control_category': row[2],
                    'description': row[3],
                    'implementation_status': row[4],
                    'last_tested': row[5],
                    'test_results': row[6]
                })

            return controls

        except Exception as e:
            self.logger.error(f"Failed to get controls: {e}")
            return []


class PCIDSSComplianceEngine:
    """
    PCI DSS compliance framework
    Payment card industry standards
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize PCI DSS compliance engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get('pci_dss.enabled', False)

        self.logger.info("PCI DSS Compliance Framework initialized")

    def log_audit_event(self, event_data: Dict) -> bool:
        """
        Log PCI DSS audit event

        Args:
            event_data: Event information

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                """INSERT INTO pci_dss_audit_log 
                   (event_type, user_id, ip_address, action, result)
                   VALUES (?, ?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO pci_dss_audit_log 
                   (event_type, user_id, ip_address, action, result)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    event_data['event_type'],
                    event_data.get('user_id'),
                    event_data.get('ip_address'),
                    event_data['action'],
                    event_data.get('result', 'success')
                )
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            return False

    def get_audit_log(self, limit: int = 1000, event_type: Optional[str] = None) -> List[Dict]:
        """
        Get PCI DSS audit log

        Args:
            limit: Maximum number of records
            event_type: Filter by event type

        Returns:
            List of audit log dictionaries
        """
        try:
            if event_type:
                result = self.db.execute(
                    """SELECT * FROM pci_dss_audit_log 
                       WHERE event_type = ? 
                       ORDER BY timestamp DESC LIMIT ?"""
                    if self.db.db_type == 'sqlite'
                    else """SELECT * FROM pci_dss_audit_log 
                       WHERE event_type = %s 
                       ORDER BY timestamp DESC LIMIT %s""",
                    (event_type, limit)
                )
            else:
                result = self.db.execute(
                    """SELECT * FROM pci_dss_audit_log 
                       ORDER BY timestamp DESC LIMIT ?"""
                    if self.db.db_type == 'sqlite'
                    else """SELECT * FROM pci_dss_audit_log 
                       ORDER BY timestamp DESC LIMIT %s""",
                    (limit,)
                )

            logs = []
            for row in (result or []):
                logs.append({
                    'event_type': row[1],
                    'user_id': row[2],
                    'ip_address': row[3],
                    'action': row[4],
                    'result': row[5],
                    'timestamp': row[6]
                })

            return logs

        except Exception as e:
            self.logger.error(f"Failed to get audit log: {e}")
            return []
