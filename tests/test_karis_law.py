#!/usr/bin/env python3
"""
Tests for Kari's Law compliance module

Kari's Law requires multi-line telephone systems (MLTS) to:
1. Allow direct dialing of 911 without prefix
2. Route emergency calls immediately
3. Notify designated contacts automatically
"""

from typing import Any
from unittest.mock import MagicMock


from pbx.features.karis_law import KarisLawCompliance


def create_mock_pbx() -> MagicMock:
    """Create mock PBX core for testing"""
    pbx = MagicMock()

    # Mock extension registry
    pbx.extension_registry = MagicMock()
    pbx.extension_registry.get_extension = MagicMock(
        return_value={
            "extension": "1001",
            "name": "Test User",
            "email": "test@example.com",
            "department": "Engineering",
        }
    )

    # Mock trunk system
    pbx.trunk_system = MagicMock()
    pbx.trunk_system.route_outbound = MagicMock(
        return_value=(
            MagicMock(trunk_id="test_trunk", name="Test Trunk", can_make_call=lambda: True),
            "911",
        )
    )
    pbx.trunk_system.get_trunk = MagicMock(
        return_value=MagicMock(
            trunk_id="emergency_trunk", name="Emergency Trunk", can_make_call=lambda: True
        )
    )

    # Mock emergency notification
    pbx.emergency_notification = MagicMock()
    pbx.emergency_notification.enabled = True
    pbx.emergency_notification.on_911_call = MagicMock()

    # Mock E911 location
    pbx.e911_location = MagicMock()
    pbx.e911_location.enabled = True
    pbx.e911_location.get_location = MagicMock(
        return_value={
            "building": "Building A",
            "floor": "2",
            "room": "205",
            "dispatchable_location": "Building A, Floor 2, Room 205, 123 Main St, City, State 12345",
        }
    )

    return pbx


def test_emergency_number_detection() -> None:
    """Test that emergency numbers are correctly detected"""

    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)

    # Test direct 911 (Kari's Law compliant)
    assert karis_law.is_emergency_number("911"), "Should detect direct 911"
    assert karis_law.is_direct_911("911"), "Should detect direct 911"

    # Test legacy prefixed numbers (should still be detected)
    assert karis_law.is_emergency_number("9911"), "Should detect 9911"
    assert karis_law.is_emergency_number("9-911"), "Should detect 9-911"
    assert not karis_law.is_direct_911("9911"), "9911 is not direct 911"
    assert not karis_law.is_direct_911("9-911"), "9-911 is not direct 911"

    # Test non-emergency numbers
    assert not karis_law.is_emergency_number("1001"), "Should not detect internal extension"
    assert not karis_law.is_emergency_number("5551234567"), "Should not detect regular number"
    assert not karis_law.is_emergency_number("811"), "Should not detect 811"
    assert not karis_law.is_emergency_number("9111"), "Should not detect 9111"


def test_emergency_number_normalization() -> None:
    """Test normalization of emergency numbers"""

    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)

    # Test normalization of various formats
    assert karis_law.normalize_emergency_number("911") == "911", "911 should remain 911"
    assert karis_law.normalize_emergency_number("9911") == "911", "9911 should normalize to 911"
    assert karis_law.normalize_emergency_number("9-911") == "911", "9-911 should normalize to 911"

    # Non-emergency numbers should remain unchanged
    assert (
        karis_law.normalize_emergency_number("1001") == "1001"
    ), "Regular number should not change"


def test_direct_911_dialing() -> None:
    """Test direct 911 dialing (Kari's Law requirement)"""

    pbx = create_mock_pbx()
    config = {
        "features": {
            "karis_law": {
                "enabled": True,
                "auto_notify": True,
                "emergency_trunk_id": "emergency_trunk",
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)

    # Test direct 911 call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="911",
        call_id="test-call-1",
        from_addr=("192.168.1.100", 5060),
    )

    assert success, "Direct 911 call should succeed"
    assert routing_info["success"], "Routing should succeed"
    assert routing_info["trunk_id"] == "emergency_trunk", "Should use emergency trunk"
    assert routing_info["destination"] == "911", "Destination should be 911"

    # Verify emergency notification was triggered
    assert (
        pbx.emergency_notification.on_911_call.called
    ), "Emergency notification should be triggered"


def test_legacy_prefix_support() -> None:
    """Test that legacy prefixes (9911, 9-911) still work but are normalized"""

    pbx = create_mock_pbx()
    config = {"features": {"karis_law": {"enabled": True, "auto_notify": True}}}
    karis_law = KarisLawCompliance(pbx, config)

    # Test 9911
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="9911",
        call_id="test-call-2",
        from_addr=("192.168.1.100", 5060),
    )

    assert success, "9911 call should succeed"
    assert routing_info["destination"] == "911", "Should normalize to 911"

    # Test 9-911
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="9-911",
        call_id="test-call-3",
        from_addr=("192.168.1.100", 5060),
    )

    assert success, "9-911 call should succeed"
    assert routing_info["destination"] == "911", "Should normalize to 911"


def test_automatic_notification() -> None:
    """Test automatic notification to designated contacts"""

    pbx = create_mock_pbx()
    config = {"features": {"karis_law": {"enabled": True, "auto_notify": True}}}
    karis_law = KarisLawCompliance(pbx, config)

    # Make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="911",
        call_id="test-call-4",
        from_addr=("192.168.1.100", 5060),
    )

    assert success, "Emergency call should succeed"

    # Verify notification was triggered
    assert pbx.emergency_notification.on_911_call.called, "Notification should be triggered"

    # Verify notification details
    call_args = pbx.emergency_notification.on_911_call.call_args
    assert call_args[1]["caller_extension"] == "1001", "Should include caller extension"
    assert call_args[1]["caller_name"] == "Test User", "Should include caller name"
    assert "location" in call_args[1], "Should include location"


def test_location_information() -> None:
    """Test location information provision (Ray Baum's Act)"""

    pbx = create_mock_pbx()
    config = {"features": {"karis_law": {"enabled": True, "require_location": True}}}
    karis_law = KarisLawCompliance(pbx, config)

    # Get location info
    location = karis_law._get_location_info("1001")

    assert location is not None, "Location should be available"
    assert "building" in location, "Should include building"
    assert "dispatchable_location" in location, "Should include dispatchable location"


def test_emergency_call_history() -> None:
    """Test emergency call history tracking"""

    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)

    # Make multiple emergency calls
    for i in range(3):
        karis_law.handle_emergency_call(
            caller_extension=f"100{i}",
            dialed_number="911",
            call_id=f"test-call-{i}",
            from_addr=("192.168.1.100", 5060),
        )

    # Get history
    history = karis_law.get_emergency_call_history()

    assert len(history) == 3, "Should have 3 calls in history"

    # Test filtering by extension
    history_filtered = karis_law.get_emergency_call_history(extension="1001")
    assert len(history_filtered) == 1, "Should have 1 call from extension 1001"


def test_compliance_validation() -> None:
    """Test compliance validation"""

    pbx = create_mock_pbx()
    config = {"features": {"karis_law": {"enabled": True, "emergency_trunk_id": "emergency_trunk"}}}
    karis_law = KarisLawCompliance(pbx, config)

    # Validate compliance
    results = karis_law.validate_compliance()

    assert results["compliant"], "Should be compliant"
    assert len(results["errors"]) == 0, "Should have no errors"


def test_disabled_compliance() -> None:
    """Test behavior when compliance is disabled"""

    pbx = create_mock_pbx()
    config = {"features": {"karis_law": {"enabled": False}}}
    karis_law = KarisLawCompliance(pbx, config)

    # Try to make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="911",
        call_id="test-call-disabled",
        from_addr=("192.168.1.100", 5060),
    )

    assert not success, "Call should fail when compliance is disabled"
    assert "error" in routing_info, "Should have error message"

    # Validate should show non-compliant
    results = karis_law.validate_compliance()
    assert not results["compliant"], "Should not be compliant"
    assert "disabled" in results["errors"][0].lower(), "Error should mention disabled"


def test_no_trunk_available() -> None:
    """Test behavior when no trunk is available"""

    pbx = create_mock_pbx()
    pbx.trunk_system.route_outbound = MagicMock(return_value=(None, None))
    pbx.trunk_system.get_trunk = MagicMock(return_value=None)

    karis_law = KarisLawCompliance(pbx)

    # Try to make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="911",
        call_id="test-call-no-trunk",
        from_addr=("192.168.1.100", 5060),
    )

    # Call should succeed but routing should fail
    assert success, "Call handling should complete"
    assert not routing_info["success"], "Routing should fail"
    assert "error" in routing_info, "Should have error message"


def test_statistics() -> None:
    """Test statistics reporting"""

    pbx = create_mock_pbx()
    config = {
        "features": {
            "karis_law": {
                "enabled": True,
                "auto_notify": True,
                "require_location": True,
                "emergency_trunk_id": "emergency_trunk",
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)

    # Make some calls
    karis_law.handle_emergency_call("1001", "911", "call-1", ("192.168.1.100", 5060))
    karis_law.handle_emergency_call("1002", "911", "call-2", ("192.168.1.101", 5060))

    # Get statistics
    stats = karis_law.get_statistics()

    assert stats["enabled"], "Should be enabled"
    assert stats["total_emergency_calls"] == 2, "Should have 2 calls"
    assert stats["auto_notify"], "Auto-notify should be enabled"
    assert stats["require_location"], "Location should be required"
    assert stats["emergency_trunk_configured"], "Emergency trunk should be configured"


def test_multi_site_e911_routing() -> None:
    """Test multi-site E911 routing with site-specific trunks"""

    pbx = create_mock_pbx()

    # Mock database with multi-site configuration
    pbx.database = MagicMock()
    pbx.database.enabled = True
    pbx.database.db_type = "sqlite"

    # Mock nomadic E911 location with IP address
    mock_location_row = (
        1,
        "1001",
        "192.168.10.50",
        "Factory Building A",
        "123 Factory Lane",
        "Detroit",
        "MI",
        "48201",
        "USA",
        "Building A",
        "1",
        "Assembly Line 3",
        None,
        None,
        "2025-12-15 10:00:00",
        True,
    )

    # Mock site configuration
    mock_site_row = (
        1,
        "Factory Building A",
        "192.168.10.1",
        "192.168.10.255",
        "site_a_emergency_trunk",
        "911",
        "+13135551234",
        "123 Factory Lane",
        "Detroit",
        "MI",
        "48201",
        "USA",
        "Building A",
        "",
    )

    # Track database call count to return appropriate results
    call_count = [0]

    def mock_execute(query: str, params: Any = None) -> list[Any]:
        call_count[0] += 1
        # Return location for first query, site for second and third
        if "nomadic_e911_locations" in query:
            return [mock_location_row]
        elif "multi_site_e911_configs" in query:
            return [mock_site_row]
        return []

    pbx.database.execute = mock_execute

    # Mock site-specific trunk
    site_trunk = MagicMock(trunk_id="site_a_emergency_trunk", name="Site A Emergency")
    site_trunk.can_make_call = MagicMock(return_value=True)

    def get_trunk(trunk_id: str) -> MagicMock:
        if trunk_id == "site_a_emergency_trunk":
            return site_trunk
        return MagicMock(trunk_id=trunk_id, name="Default Trunk", can_make_call=lambda: True)

    pbx.trunk_system.get_trunk = get_trunk

    config = {
        "features": {
            "karis_law": {
                "enabled": True,
                "auto_notify": True,
                "emergency_trunk_id": "global_emergency_trunk",
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)

    # Make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension="1001",
        dialed_number="911",
        call_id="test-multi-site",
        from_addr=("192.168.10.50", 5060),
    )

    assert success, "Emergency call should succeed"
    assert routing_info["success"], "Routing should succeed"
    assert (
        routing_info["trunk_id"] == "site_a_emergency_trunk"
    ), "Should use site-specific emergency trunk"
    assert routing_info.get("site_specific"), "Should be marked as site-specific routing"
    assert routing_info.get("psap_number") == "911", "Should include PSAP number"
    assert routing_info.get("elin") == "+13135551234", "Should include ELIN"
