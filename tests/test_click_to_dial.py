#!/usr/bin/env python3
"""
Test Click-to-Dial functionality
"""
import os
import sqlite3
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.click_to_dial import ClickToDialEngine


class MockDB:
    """Mock database for testing"""

    def __init__(self):
        self.db_type = "sqlite"
        self.conn = sqlite3.connect(":memory:")
        self.enabled = True
        self._init_tables()

    def _init_tables(self):
        """Initialize test tables"""
        # Click-to-dial configs
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS click_to_dial_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL UNIQUE,
                enabled INTEGER DEFAULT 1,
                default_caller_id TEXT,
                auto_answer INTEGER DEFAULT 0,
                browser_notification INTEGER DEFAULT 1
            )
        """
        )

        # Click-to-dial history
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS click_to_dial_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL,
                destination TEXT NOT NULL,
                call_id TEXT NOT NULL,
                source TEXT DEFAULT 'web',
                initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                connected_at TIMESTAMP,
                status TEXT DEFAULT 'initiated'
            )
        """
        )
        self.conn.commit()

    def execute(self, query, params=None):
        """Execute query"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor.fetchall()

    def close(self):
        """Close connection"""
        self.conn.close()


def test_click_to_dial_init():
    """Test click-to-dial engine initialization"""
    print("Testing click-to-dial initialization...")

    config = {"click_to_dial.enabled": True}
    db = MockDB()

    # Initialize without PBX core (framework mode)
    engine = ClickToDialEngine(db, config)
    assert engine.enabled is True
    assert engine.pbx_core is None
    print("  ✓ Engine initialized successfully")

    # Initialize with mock PBX core
    class MockPBXCore:
        def __init__(self):
            self.call_manager = None

    mock_pbx = MockPBXCore()
    engine_with_pbx = ClickToDialEngine(db, config, mock_pbx)
    assert engine_with_pbx.pbx_core is mock_pbx
    print("  ✓ Engine initialized with PBX core")

    db.close()


def test_click_to_dial_config():
    """Test click-to-dial configuration management"""
    print("\nTesting click-to-dial configuration...")

    config = {"click_to_dial.enabled": True}
    db = MockDB()

    engine = ClickToDialEngine(db, config)

    # Update configuration
    test_config = {
        "enabled": True,
        "default_caller_id": "1001",
        "auto_answer": True,
        "browser_notification": True,
    }

    result = engine.update_config("1001", test_config)
    assert result is True
    print("  ✓ Configuration updated")

    # Get configuration
    retrieved_config = engine.get_config("1001")
    assert retrieved_config is not None
    assert retrieved_config["extension"] == "1001"
    assert retrieved_config["enabled"] is True
    assert retrieved_config["auto_answer"] is True
    print("  ✓ Configuration retrieved")

    db.close()


def test_click_to_dial_call_initiation():
    """Test click-to-dial call initiation (framework mode)"""
    print("\nTesting click-to-dial call initiation...")

    config = {"click_to_dial.enabled": True}
    db = MockDB()

    engine = ClickToDialEngine(db, config)

    # Initiate call (framework mode - no PBX core)
    call_id = engine.initiate_call("1001", "5551234", "web")
    assert call_id is not None
    assert call_id.startswith("c2d-1001-")
    print(f"  ✓ Call initiated (framework mode): {call_id}")

    # Get call history
    history = engine.get_call_history("1001")
    assert len(history) == 1
    assert history[0]["destination"] == "5551234"
    assert history[0]["status"] == "initiated"
    print("  ✓ Call history retrieved")

    # Update call status
    result = engine.update_call_status(call_id, "connected")
    assert result is True

    history = engine.get_call_history("1001")
    assert history[0]["status"] == "connected"
    print("  ✓ Call status updated")

    db.close()


def test_click_to_dial_with_mock_pbx():
    """Test click-to-dial with mock PBX core"""
    print("\nTesting click-to-dial with mock PBX core...")

    config = {"click_to_dial.enabled": True}
    db = MockDB()

    # Create mock PBX core with call manager
    class MockCall:
        def __init__(self, call_id, from_ext, to_ext):
            self.call_id = call_id
            self.from_extension = from_ext
            self.to_extension = to_ext

        def start(self):
            pass

    class MockCallManager:
        def create_call(self, call_id, from_extension, to_extension):
            return MockCall(call_id, from_extension, to_extension)

    class MockPBXCore:
        def __init__(self):
            self.call_manager = MockCallManager()

    mock_pbx = MockPBXCore()
    engine = ClickToDialEngine(db, config, mock_pbx)

    # Initiate call with PBX integration
    call_id = engine.initiate_call("1001", "5551234", "web")
    assert call_id is not None
    print(f"  ✓ Call initiated with PBX integration: {call_id}")

    # Verify call history shows ringing status
    history = engine.get_call_history("1001")
    assert len(history) == 1
    assert history[0]["status"] == "ringing"
    print("  ✓ Call status set to 'ringing' via PBX integration")

    db.close()


def test_click_to_dial_all_configs():
    """Test getting all click-to-dial configurations"""
    print("\nTesting get all configurations...")

    config = {"click_to_dial.enabled": True}
    db = MockDB()

    engine = ClickToDialEngine(db, config)

    # Add multiple configurations
    for ext in ["1001", "1002", "1003"]:
        engine.update_config(ext, {"enabled": True, "auto_answer": False})

    # Get all configs
    all_configs = engine.get_all_configs()
    assert len(all_configs) == 3
    assert all([c["extension"] in ["1001", "1002", "1003"] for c in all_configs])
    print(f"  ✓ Retrieved {len(all_configs)} configurations")

    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Click-to-Dial Feature Tests")
    print("=" * 60)

    try:
        test_click_to_dial_init()
        test_click_to_dial_config()
        test_click_to_dial_call_initiation()
        test_click_to_dial_with_mock_pbx()
        test_click_to_dial_all_configs()

        print("\n" + "=" * 60)
        print("✅ All Click-to-Dial Tests Passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
