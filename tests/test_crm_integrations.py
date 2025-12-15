"""
Tests for CRM Integrations Framework (HubSpot and Zendesk)
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.features.crm_integrations import HubSpotIntegration, ZendeskIntegration


class TestHubSpotIntegration(unittest.TestCase):
    """Test HubSpot integration functionality"""

    def setUp(self):
        """Set up test database"""
        import sqlite3
        
        class MockDB:
            def __init__(self):
                self.db_type = 'sqlite'
                self.conn = sqlite3.connect(':memory:')
                self.enabled = True
                
            def execute(self, query, params=None):
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()
                
            def disconnect(self):
                self.conn.close()
        
        self.db = MockDB()
        
        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS hubspot_integration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled INTEGER DEFAULT 0,
                api_key_encrypted TEXT,
                portal_id TEXT,
                sync_contacts INTEGER DEFAULT 0,
                sync_deals INTEGER DEFAULT 0,
                auto_create_contacts INTEGER DEFAULT 0,
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS integration_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_type TEXT,
                action TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.config = {}
        self.integration = HubSpotIntegration(self.db, self.config)

    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self):
        """Test integration initialization"""
        self.assertIsNotNone(self.integration)
        self.assertFalse(self.integration.enabled)

    def test_update_config(self):
        """Test updating configuration"""
        config = {
            'enabled': True,
            'api_key': 'test-key-123',
            'portal_id': '12345',
            'webhook_url': 'https://webhook.example.com/hubspot'
        }
        
        result = self.integration.update_config(config)
        self.assertTrue(result)

    def test_get_config(self):
        """Test retrieving configuration"""
        # First create a config
        config = {
            'enabled': True,
            'api_key': 'test-key-456',
            'portal_id': '67890'
        }
        self.integration.update_config(config)
        
        # Now retrieve it
        retrieved = self.integration.get_config()
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved['enabled'])
        self.assertEqual(retrieved['portal_id'], '67890')

    def test_sync_contact_disabled(self):
        """Test sync contact when integration is disabled"""
        contact = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        result = self.integration.sync_contact(contact)
        self.assertFalse(result)

    def test_create_deal_disabled(self):
        """Test create deal when integration is disabled"""
        deal = {
            'dealname': 'Test Deal',
            'amount': 1000
        }
        
        result = self.integration.create_deal(deal)
        self.assertFalse(result)


class TestZendeskIntegration(unittest.TestCase):
    """Test Zendesk integration functionality"""

    def setUp(self):
        """Set up test database"""
        import sqlite3
        
        class MockDB:
            def __init__(self):
                self.db_type = 'sqlite'
                self.conn = sqlite3.connect(':memory:')
                self.enabled = True
                
            def execute(self, query, params=None):
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()
                
            def disconnect(self):
                self.conn.close()
        
        self.db = MockDB()
        
        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS zendesk_integration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled INTEGER DEFAULT 0,
                subdomain TEXT,
                api_token_encrypted TEXT,
                email TEXT,
                auto_create_tickets INTEGER DEFAULT 0,
                default_priority TEXT DEFAULT 'normal',
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS integration_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_type TEXT,
                action TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.config = {}
        self.integration = ZendeskIntegration(self.db, self.config)

    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self):
        """Test integration initialization"""
        self.assertIsNotNone(self.integration)
        self.assertFalse(self.integration.enabled)

    def test_update_config(self):
        """Test updating configuration"""
        config = {
            'enabled': True,
            'subdomain': 'testcompany',
            'api_token': 'test-token-123',
            'email': 'admin@example.com',
            'default_priority': 'high',
            'webhook_url': 'https://webhook.example.com/zendesk'
        }
        
        result = self.integration.update_config(config)
        self.assertTrue(result)

    def test_get_config(self):
        """Test retrieving configuration"""
        # First create a config
        config = {
            'enabled': True,
            'subdomain': 'mycompany',
            'api_token': 'token-456',
            'email': 'support@example.com'
        }
        self.integration.update_config(config)
        
        # Now retrieve it
        retrieved = self.integration.get_config()
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved['enabled'])
        self.assertEqual(retrieved['subdomain'], 'mycompany')

    def test_create_ticket_disabled(self):
        """Test create ticket when integration is disabled"""
        ticket = {
            'subject': 'Test Ticket',
            'description': 'This is a test',
            'requester_email': 'customer@example.com'
        }
        
        result = self.integration.create_ticket(ticket)
        self.assertIsNone(result)

    def test_update_ticket_disabled(self):
        """Test update ticket when integration is disabled"""
        result = self.integration.update_ticket('123', {'status': 'solved'})
        self.assertFalse(result)

    def test_activity_logging(self):
        """Test that integration activity is logged"""
        # Enable integration
        config = {
            'enabled': True,
            'subdomain': 'testco',
            'api_token': 'token',
            'email': 'test@test.com'
        }
        self.integration.update_config(config)
        
        # Try to create a ticket (will fail without real API, but should log)
        ticket = {
            'subject': 'Test',
            'description': 'Test ticket'
        }
        self.integration.create_ticket(ticket)
        
        # Check activity log
        logs = self.db.execute("SELECT * FROM integration_activity_log")
        self.assertGreater(len(logs), 0)


if __name__ == '__main__':
    unittest.main()
