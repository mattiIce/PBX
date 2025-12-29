"""
Test suite for Auto Attendant Submenu functionality
"""

import os
import shutil
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.features.auto_attendant import AAState, AutoAttendant, DestinationType


class TestAutoAttendantSubmenu(unittest.TestCase):
    """Test Auto Attendant Submenu functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")

        # Create a mock config
        self.config_data = {
            "auto_attendant": {
                "enabled": True,
                "extension": "0",
                "timeout": 10,
                "max_retries": 3,
                "operator_extension": "1001",
                "audio_path": os.path.join(self.test_dir, "audio"),
            },
            "database": {"path": self.db_path},
        }

        # Create mock config object
        self.config = MockConfig(self.config_data)

        # Initialize auto attendant
        self.aa = AutoAttendant(self.config)

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_database_initialization(self):
        """Test that submenu tables are created"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check that auto_attendant_menus table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auto_attendant_menus'")
        self.assertIsNotNone(cursor.fetchone())

        # Check that auto_attendant_menu_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auto_attendant_menu_items'")
        self.assertIsNotNone(cursor.fetchone())

        # Check that main menu was created
        cursor.execute("SELECT COUNT(*) FROM auto_attendant_menus WHERE menu_id = 'main'")
        self.assertEqual(cursor.fetchone()[0], 1)

        conn.close()

    def test_create_submenu(self):
        """Test creating a submenu"""
        success = self.aa.create_menu(
            menu_id="shipping-submenu",
            parent_menu_id="main",
            menu_name="Shipping and Receiving",
            prompt_text="For directions, press 1. For shipping, press 2.",
        )

        self.assertTrue(success)

        # Verify menu was created
        menu = self.aa.get_menu("shipping-submenu")
        self.assertIsNotNone(menu)
        self.assertEqual(menu["menu_id"], "shipping-submenu")
        self.assertEqual(menu["parent_menu_id"], "main")
        self.assertEqual(menu["menu_name"], "Shipping and Receiving")

    def test_circular_reference_prevention(self):
        """Test that circular references are prevented"""
        # Create two menus
        self.aa.create_menu("menu1", "main", "Menu 1", "Menu 1 prompt")
        self.aa.create_menu("menu2", "menu1", "Menu 2", "Menu 2 prompt")

        # Try to create circular reference: menu1 -> menu2 -> menu1
        success = self.aa.create_menu("menu3", "menu2", "Menu 3", "Menu 3 prompt")
        self.assertTrue(success)

        # Now try to make menu1 a child of menu3 (would create a circle)
        # This should be prevented when we try to update parent_menu_id
        # For now, test that the check function works
        would_create_circle = self.aa._would_create_circular_reference("menu1", "menu3")
        self.assertTrue(would_create_circle)

    def test_menu_depth_validation(self):
        """Test that menu depth is limited to 5 levels"""
        # Create a chain of menus
        parent = "main"
        for i in range(1, 6):
            menu_id = f"level{i}"
            success = self.aa.create_menu(menu_id, parent, f"Level {i}", f"Level {i} prompt")
            self.assertTrue(success)
            parent = menu_id

        # Try to create a 6th level (should fail)
        success = self.aa.create_menu("level6", "level5", "Level 6", "Level 6 prompt")
        self.assertFalse(success)

    def test_add_menu_item_extension(self):
        """Test adding extension-type menu item"""
        success = self.aa.add_menu_item("main", "1", "extension", "1001", "Sales Department")

        self.assertTrue(success)

        # Verify item was added
        items = self.aa.get_menu_items("main")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["digit"], "1")
        self.assertEqual(items[0]["destination_type"], "extension")
        self.assertEqual(items[0]["destination_value"], "1001")

    def test_add_menu_item_submenu(self):
        """Test adding submenu-type menu item"""
        # Create a submenu first
        self.aa.create_menu("sales-submenu", "main", "Sales", "Sales submenu")

        # Add menu item pointing to submenu
        success = self.aa.add_menu_item("main", "1", "submenu", "sales-submenu", "Sales Department")

        self.assertTrue(success)

        # Verify item was added
        items = self.aa.get_menu_items("main")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["destination_type"], "submenu")
        self.assertEqual(items[0]["destination_value"], "sales-submenu")

    def test_add_menu_item_invalid_submenu(self):
        """Test that adding menu item with non-existent submenu fails"""
        success = self.aa.add_menu_item("main", "1", "submenu", "nonexistent", "Invalid")

        self.assertFalse(success)

    def test_get_menu_tree(self):
        """Test getting complete menu tree"""
        # Create a menu structure
        self.aa.create_menu("sales", "main", "Sales", "Sales menu")
        self.aa.create_menu("support", "main", "Support", "Support menu")
        self.aa.create_menu("billing", "sales", "Billing", "Billing submenu")

        # Add menu items
        self.aa.add_menu_item("main", "1", "submenu", "sales", "Sales")
        self.aa.add_menu_item("main", "2", "submenu", "support", "Support")
        self.aa.add_menu_item("sales", "1", "submenu", "billing", "Billing")
        self.aa.add_menu_item("sales", "2", "extension", "1001", "Sales Rep")

        # Get menu tree
        tree = self.aa.get_menu_tree("main")

        self.assertIsNotNone(tree)
        self.assertEqual(tree["menu_id"], "main")
        self.assertEqual(len(tree["items"]), 2)

        # Check first item (sales submenu)
        sales_item = tree["items"][0]
        self.assertEqual(sales_item["destination_type"], "submenu")
        self.assertIn("submenu", sales_item)
        self.assertEqual(len(sales_item["submenu"]["items"]), 2)

    def test_delete_menu(self):
        """Test deleting a menu"""
        # Create a submenu
        self.aa.create_menu("test-menu", "main", "Test Menu", "Test prompt")

        # Delete it
        success = self.aa.delete_menu("test-menu")
        self.assertTrue(success)

        # Verify it's gone
        menu = self.aa.get_menu("test-menu")
        self.assertIsNone(menu)

    def test_delete_main_menu_fails(self):
        """Test that main menu cannot be deleted"""
        success = self.aa.delete_menu("main")
        self.assertFalse(success)

    def test_delete_referenced_menu_fails(self):
        """Test that a menu referenced by items cannot be deleted"""
        # Create a submenu and reference it
        self.aa.create_menu("referenced", "main", "Referenced Menu", "Prompt")
        self.aa.add_menu_item("main", "1", "submenu", "referenced", "Go to submenu")

        # Try to delete (should fail)
        success = self.aa.delete_menu("referenced")
        self.assertFalse(success)

    def test_submenu_navigation(self):
        """Test navigating to a submenu"""
        # Create a submenu
        self.aa.create_menu("sales", "main", "Sales", "Sales menu")
        self.aa.add_menu_item("main", "1", "submenu", "sales", "Sales")
        self.aa.add_menu_item("sales", "1", "extension", "1001", "Sales Rep")

        # Start a session
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Navigate to sales submenu
        result = self.aa.handle_dtmf(session, "1")

        self.assertEqual(result["action"], "play")
        self.assertEqual(session["state"], AAState.SUBMENU)
        self.assertEqual(session["current_menu_id"], "sales")
        self.assertEqual(len(session["menu_stack"]), 1)
        self.assertEqual(session["menu_stack"][0], "main")

    def test_go_back_navigation(self):
        """Test going back to previous menu with * key"""
        # Create submenu structure
        self.aa.create_menu("sales", "main", "Sales", "Sales menu")
        self.aa.add_menu_item("main", "1", "submenu", "sales", "Sales")

        # Start session and navigate to submenu
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]
        result = self.aa.handle_dtmf(session, "1")  # Navigate to sales

        # Go back with *
        result = self.aa.handle_dtmf(session, "*")

        self.assertEqual(result["action"], "play")
        self.assertEqual(session["current_menu_id"], "main")
        self.assertEqual(session["state"], AAState.MAIN_MENU)
        self.assertEqual(len(session["menu_stack"]), 0)

    def test_repeat_menu(self):
        """Test repeating current menu with # key"""
        # Start session
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Press # to repeat
        result = self.aa.handle_dtmf(session, "#")

        self.assertEqual(result["action"], "play")
        self.assertEqual(session["current_menu_id"], "main")

    def test_transfer_from_submenu(self):
        """Test transferring from a submenu"""
        # Create submenu with extension
        self.aa.create_menu("sales", "main", "Sales", "Sales menu")
        self.aa.add_menu_item("main", "1", "submenu", "sales", "Sales")
        self.aa.add_menu_item("sales", "1", "extension", "1001", "Sales Rep")

        # Start session and navigate to submenu
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]
        result = self.aa.handle_dtmf(session, "1")  # Navigate to sales
        session = result["session"]

        # Transfer to extension
        result = self.aa.handle_dtmf(session, "1")

        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "1001")
        self.assertEqual(session["state"], AAState.TRANSFERRING)

    def test_list_menus(self):
        """Test listing all menus"""
        # Create some menus
        self.aa.create_menu("sales", "main", "Sales", "Sales menu")
        self.aa.create_menu("support", "main", "Support", "Support menu")

        # List menus
        menus = self.aa.list_menus()

        self.assertGreaterEqual(len(menus), 3)  # main + sales + support
        menu_ids = [m["menu_id"] for m in menus]
        self.assertIn("main", menu_ids)
        self.assertIn("sales", menu_ids)
        self.assertIn("support", menu_ids)

    def test_update_menu(self):
        """Test updating a menu"""
        # Create a menu
        self.aa.create_menu("test", "main", "Test Menu", "Original prompt")

        # Update it
        success = self.aa.update_menu("test", menu_name="Updated Test", prompt_text="New prompt")
        self.assertTrue(success)

        # Verify changes
        menu = self.aa.get_menu("test")
        self.assertEqual(menu["menu_name"], "Updated Test")
        self.assertEqual(menu["prompt_text"], "New prompt")

    def test_destination_type_enum(self):
        """Test DestinationType enum"""
        self.assertEqual(DestinationType.EXTENSION.value, "extension")
        self.assertEqual(DestinationType.SUBMENU.value, "submenu")
        self.assertEqual(DestinationType.QUEUE.value, "queue")
        self.assertEqual(DestinationType.VOICEMAIL.value, "voicemail")
        self.assertEqual(DestinationType.OPERATOR.value, "operator")

    def test_backward_compatibility_with_legacy_menu(self):
        """Test that legacy menu_options still work"""
        # Add a legacy menu option directly to the old table
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO auto_attendant_menu_options (digit, destination, description) VALUES (?, ?, ?)",
            ("5", "1005", "Legacy Option"),
        )
        conn.commit()
        conn.close()

        # Reload menu options
        self.aa._load_menu_options_from_db()

        # Verify it's in the legacy menu_options
        self.assertIn("5", self.aa.menu_options)
        self.assertEqual(self.aa.menu_options["5"]["destination"], "1005")

        # Test that it still works in navigation
        result = self.aa.start_session("test-call", "1001")
        session = result["session"]
        result = self.aa.handle_dtmf(session, "5")

        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "1005")


class MockConfig:
    """Mock configuration object for testing"""

    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        """Get configuration value"""
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default


if __name__ == "__main__":
    unittest.main()
